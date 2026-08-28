"""Pre-registration freeze. Frozen protocols are immutable."""

from __future__ import annotations

from typing import Any

from engineering_os.evaluation import CONTRACT_VERSION as PHASE4
from engineering_os.experiments import CONTRACT_VERSION
from engineering_os.experiments.config_snapshot import canonical_dumps, sha256_text, variant_snapshot
from engineering_os.experiments.diff import validate_single_factor
from engineering_os.experiments.fingerprint import environment_fingerprint
from engineering_os.performance import CONTRACT_VERSION as PHASE5

PHASE3 = "phase3-v1"


def _variant(definition: dict[str, Any], role: str, env: dict[str, Any], contracts: dict[str, Any]) -> dict[str, Any]:
    spec = definition[role]
    return variant_snapshot(
        variant_id=spec["variant_id"],
        variant_name=spec.get("variant_name") or role,
        treatment_dimension=definition["treatment_dimension"],
        artifact={"name": spec.get("artifact")},
        model=spec.get("model") or {},
        profile=spec.get("profile") or {},
        prompt=spec.get("prompt") or {},
        skills=spec.get("skills") or {},
        tools=spec.get("tools") or {},
        environment=env["snapshot"],
        contracts=contracts,
    )


def freeze(definition: dict[str, Any]) -> dict[str, Any]:
    env = environment_fingerprint()
    contracts = {
        "phase3_ruleset": PHASE3,
        "phase4_contract": PHASE4,
        "phase5_contract": PHASE5,
        "phase6_contract": CONTRACT_VERSION,
    }
    control = _variant(definition, "control", env, contracts)
    candidate = _variant(definition, "candidate", env, contracts)
    diff = validate_single_factor(
        definition["treatment_dimension"],
        control["snapshot"],
        candidate["snapshot"],
    )
    if not diff["ok"]:
        raise ValueError(diff["reason"] + f" diffs={diff['diffs']}")
    protocol = {
        "experiment_id": definition["experiment_id"],
        "protocol_version": str(definition["version"]),
        "state": "PRE_REGISTERED",
        "scope": definition["scope"],
        "design": definition["design"],
        "treatment_dimension": definition["treatment_dimension"],
        "hypothesis": definition["hypothesis"],
        "expected_direction": definition.get("expected_direction") or "NONE",
        "primary_metric": definition["primary_metric"],
        "secondary_metrics": definition.get("secondary_metrics") or [],
        "guardrails": definition["guardrails"],
        "sample_plan": definition["sample_plan"],
        "analysis": definition["analysis"],
        "assignment": definition["assignment"],
        "budget": definition["budget"],
        "missingness": definition.get("missingness") or {"threshold": 0.25, "on_exceed": "INSUFFICIENT_DATA"},
        "invalidity": definition.get("invalidity") or {},
        "experimental_unit": definition.get("experimental_unit") or "benchmark_case_execution",
        "benchmark_suite": definition.get("benchmark_suite"),
        "cases": definition.get("cases") or [],
        "control": control,
        "candidate": candidate,
        "config_diff": diff,
        "contracts": contracts,
        "definition_hash": definition["_definition_hash"],
        "environment_hash": env["config_hash"],
        "fixture_validation_only": definition["scope"] == "FIXTURE",
    }
    protocol["pre_registration_hash"] = sha256_text(
        canonical_dumps({k: v for k, v in protocol.items() if k != "pre_registration_hash"})
    )
    return protocol


def reject_mutation(frozen_hash: str, protocol: dict[str, Any]) -> None:
    probe = {k: v for k, v in protocol.items() if k != "pre_registration_hash"}
    current = sha256_text(canonical_dumps(probe))
    stored = protocol.get("pre_registration_hash")
    if stored != frozen_hash or current != frozen_hash:
        raise PermissionError("REJECTED: frozen protocol mutation")
