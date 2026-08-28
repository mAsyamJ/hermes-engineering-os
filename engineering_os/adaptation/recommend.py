"""Deterministic Phase 6 → recommendation eligibility. No Phase 5 ranking."""

from __future__ import annotations

from typing import Any

from engineering_os.adaptation import CONTRACT_VERSION, PRODUCTION_RECOMMENDATION
from engineering_os.experiments.config_snapshot import canonical_dumps, sha256_text

REQUIRED_VALIDITY = (
    "PROTOCOL_INTEGRITY",
    "ASSIGNMENT_INTEGRITY",
    "CONFIG_INTEGRITY",
    "ENVIRONMENT_INTEGRITY",
    "EXPOSURE_FIDELITY",
    "OUTCOME_COVERAGE",
    "EVALUATOR_COMPATIBILITY",
)

BLOCKED_CONCLUSIONS = {
    "NO_CLEAR_EFFECT",
    "EVIDENCE_AGAINST_CANDIDATE",
    "INVALIDATED",
    "GUARDRAIL_FAILURE",
    "INSUFFICIENT_DATA",
    "NOT_STARTED",
    "COLLECTING",
}

REAL_TREATMENTS = {"MODEL", "PROFILE", "PROMPT", "SKILL", "TOOLS"}


def _reason_has_fixture_only(reason: str) -> bool:
    return "FIXTURE_VALIDATION_ONLY" in (reason or "")


def recommend_from_result(result: dict[str, Any]) -> dict[str, Any]:
    """Pure eligibility. Never activates a policy."""
    source = result.get("source") or "phase6"
    if source != "phase6":
        return _not_promotable(result, "Phase 5 observational ranking cannot create a recommendation")
    conclusion = result.get("conclusion") or "NOT_STARTED"
    reason = result.get("reason") or ""
    validity = result.get("validity") or {}
    guard = result.get("guardrail_state") or result.get("guardrails") or "PASS"
    if isinstance(guard, dict):
        guard = guard.get("state") or "UNKNOWN"
    scope = result.get("scope") or "FIXTURE"
    treatment = result.get("treatment_dimension") or "NONE"
    if result.get("contamination"):
        return _not_promotable(result, "contaminated experiment is not promotable")
    if guard not in {"PASS", "NA"}:
        return _not_promotable(result, f"guardrail state {guard} is not promotable")
    if conclusion in BLOCKED_CONCLUSIONS:
        return _not_promotable(result, f"conclusion {conclusion} is not promotable")
    missing = [name for name in REQUIRED_VALIDITY if (validity.get(name) or "FAIL") != "PASS"]
    if missing:
        return _not_promotable(result, f"required validity missing: {missing}")
    fixture_only = _reason_has_fixture_only(reason) or scope in {"FIXTURE", "BENCHMARK"}
    if conclusion != "EVIDENCE_FOR_CANDIDATE":
        return _not_promotable(result, f"conclusion {conclusion} is not promotable")
    production_ok = (
        not fixture_only
        and treatment in REAL_TREATMENTS
        and scope not in {"FIXTURE", "BENCHMARK"}
        and not _reason_has_fixture_only(reason)
    )
    if not production_ok:
        payload = _base(result)
        payload.update(
            {
                "classification": "TEST_ONLY",
                "state": "EVIDENCE_VALIDATED",
                "production_promotable": False,
                "production_status": PRODUCTION_RECOMMENDATION,
                "reason": "TEST_ONLY_RECOMMENDATION; FIXTURE_VALIDATION_ONLY cannot unlock production",
            }
        )
        return payload
    payload = _base(result)
    payload.update(
        {
            "classification": "PRODUCTION_CANDIDATE",
            "state": "APPROVAL_REQUIRED",
            "production_promotable": True,
            "production_status": "READY",
            "reason": "qualified Phase 6 confirmatory result",
        }
    )
    return payload


def _base(result: dict[str, Any]) -> dict[str, Any]:
    body = {
        "experiment_id": result.get("experiment_id"),
        "protocol_hash": result.get("protocol_hash") or result.get("pre_registration_hash"),
        "conclusion": result.get("conclusion"),
        "scope": result.get("scope"),
        "treatment_dimension": result.get("treatment_dimension"),
        "validity": result.get("validity") or {},
        "contract_version": CONTRACT_VERSION,
        "phase6_contract": result.get("phase6_contract") or "phase6-exp-v1",
        "candidate_config_hash": result.get("candidate_config_hash"),
        "control_config_hash": result.get("control_config_hash"),
    }
    return {
        "status": "success",
        "source": "phase6",
        "source_result": body,
        "recommendation_hash": sha256_text(canonical_dumps(body)),
        "auto_promote": False,
        "active_policy": False,
    }


def _not_promotable(result: dict[str, Any], reason: str) -> dict[str, Any]:
    payload = _base(result)
    payload.update(
        {
            "classification": "NOT_PROMOTABLE",
            "state": "NOT_PROMOTABLE",
            "production_promotable": False,
            "production_status": PRODUCTION_RECOMMENDATION,
            "reason": reason,
        }
    )
    return payload
