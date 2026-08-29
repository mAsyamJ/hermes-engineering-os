"""Independent PAR readiness cells. Never collapse into one green status."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engineering_os.adaptation import (
    APPROVAL_A_STATUS,
    APPROVAL_B_STATUS,
    CANARY_PACKAGE_STATUS,
    LLM_BUDGET_STATUS,
    MEMORY_ISOLATION,
    PAG2_READINESS,
    PAR_CONTRACT,
    PRODUCTION_ACTUATION,
    PRODUCTION_APPROVAL,
    PRODUCTION_RECOMMENDATION,
    PRODUCTION_SHADOW_STATUS,
    REAL_CAUSAL_EVIDENCE,
    REAL_EXPERIMENT,
    RUNTIME_ACTUATION,
    RUNTIME_INTEGRATION,
    SECURE_HUMAN_AUTHORITY,
    TREATMENT_FIDELITY,
    UPSTREAM_ACTUATION,
)
from engineering_os.adaptation.approval_ed25519 import production_trust_anchor_status
from engineering_os.experiments.budget_gate import budget_authorization_status

ROOT = Path(__file__).resolve().parents[2]


def _patch_present() -> bool:
    return (ROOT / "patches" / "hermes" / "0001-pre-worker-spawn-hook.patch").is_file()


def _upstream_patch_present() -> bool:
    return (ROOT / "patches" / "hermes" / "upstream" / "0001-worker-spawn-transform.patch").is_file()


def cells() -> dict[str, Any]:
    trust = production_trust_anchor_status()
    budget = budget_authorization_status()
    return {
        "secure_human_authority": SECURE_HUMAN_AUTHORITY,
        "secure_authority": SECURE_HUMAN_AUTHORITY,
        "runtime_actuation": RUNTIME_ACTUATION if _patch_present() else RUNTIME_INTEGRATION,
        "upstream_actuation": UPSTREAM_ACTUATION if _upstream_patch_present() else "BLOCKED_UPSTREAM_DRIFT",
        "memory_isolation": MEMORY_ISOLATION,
        "real_experiment_preflight": "READY",
        "budget_authorization": budget.get("status") or LLM_BUDGET_STATUS,
        "real_experiment": REAL_EXPERIMENT if not budget.get("ok") else "AUTHORIZED",
        "treatment_fidelity": TREATMENT_FIDELITY,
        "real_causal_evidence": REAL_CAUSAL_EVIDENCE,
        "production_recommendation": PRODUCTION_RECOMMENDATION,
        "pag2_readiness": PAG2_READINESS,
        "production_shadow": PRODUCTION_SHADOW_STATUS,
        "approval_a": APPROVAL_A_STATUS,
        "canary_package": CANARY_PACKAGE_STATUS,
        "approval_b": APPROVAL_B_STATUS,
        "production_adaptation": PRODUCTION_ACTUATION,
        "human_approval_boundary": PRODUCTION_APPROVAL,
        "production_evidence": PRODUCTION_RECOMMENDATION,
        "runtime_integration_live": RUNTIME_INTEGRATION,
        "llm_budget": budget.get("status") or LLM_BUDGET_STATUS,
        "trust_anchor": trust,
        "live_patch_deployed": False,
        "official_pre_spawn_seam": "NOT_FOUND",
        "contract_version": PAR_CONTRACT,
        "phase7_contract": "phase7-adapt-v1",
        "pag1_contract": "pag1-v1",
    }


def cell(name: str) -> dict[str, Any]:
    mapping = cells()
    aliases = {
        "authority": "secure_human_authority",
        "runtime": "runtime_actuation",
        "memory": "memory_isolation",
        "evidence": "real_causal_evidence",
        "canary": "canary_package",
        "pag2": "pag2_readiness",
        "experiment": "real_experiment",
        "budget": "budget_authorization",
        "upstream": "upstream_actuation",
        "fidelity": "treatment_fidelity",
        "preflight": "real_experiment_preflight",
        "recommendation": "production_recommendation",
    }
    key = aliases.get(name, name)
    if key not in mapping:
        return {"status": "NOT_FOUND", "cell": name}
    return {
        "status": "AVAILABLE",
        "cell": key,
        "value": mapping[key],
        "cells": {name: mapping[name] for name in (
            "secure_human_authority",
            "runtime_actuation",
            "upstream_actuation",
            "memory_isolation",
            "real_experiment_preflight",
            "budget_authorization",
            "real_experiment",
            "treatment_fidelity",
            "real_causal_evidence",
            "production_recommendation",
            "pag2_readiness",
            "production_shadow",
            "approval_a",
            "canary_package",
            "approval_b",
            "production_adaptation",
        ) if name in mapping},
        "collapsed": False,
        "production_adaptation": PRODUCTION_ACTUATION,
    }
